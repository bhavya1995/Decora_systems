import pymongo
import json
import gridfs
import base64
import sendgrid
import tempfile

from sendgrid.helpers.mail import *

from django.shortcuts import render

from django.http import HttpResponseRedirect
from django.http import HttpResponse, Http404
from django.http import HttpResponseForbidden

from django.contrib import auth
from django.contrib.auth.models import User
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt

from pymongo import MongoClient

from bson.json_util import dumps, loads
from bson.objectid import ObjectId

from admin_panel.utility_constants import SUCCESSFUL_LOGIN_MESSAGE, UNAUTHORIZED_LOGIN_MESSAGE, AUTHENTICATION_ERROR_MESSAGE

from django.shortcuts import render_to_response
from django.template.context import RequestContext

from admin_panel.views import generate16DigitRandomNumber, createAzureBlobService, writeFileToAzureFromRequest
# Create your views here.

def home(request):
   context = RequestContext(request,
                           {'request': request,
                            'user': request.user})
   return render_to_response('home.html',
                             context_instance=context)

def createMongoConnection():
	client = MongoClient()
	db = client[settings.DATABASE_NAME]
	return db

def sendMail(sendTo, sendFrom, subject, body):
	sg = sendgrid.SendGridAPIClient(apikey = settings.SENDGRID_KEY_ID)
	from_email = Email(sendFrom)
	subject = subject
	to_email = Email(sendTo)
	content = Content("text/plain", body)
	mail = Mail(from_email, subject, to_email, content)
	response = sg.client.mail.send.post(request_body=mail.get())

def logout(request):
	auth.logout(request)
	return HttpResponseRedirect('/admin')

def createUser(firstName, lastName, email, password):
	user = User.objects.create(
		username = email, first_name = firstName, 
		last_name = lastName, is_active = False, email = email
	);
	user.set_password(password)
	user.save()

def updateUserAvatar(avatar, db, email):
	user_collection = db['auth_user']

	fs = gridfs.GridFS(db)
	file_id = fs.put(avatar, filename = avatar.name)
	user_collection.update(
		{'username': email},
		{'$set': {'avatar_id': file_id}},
		upsert = False
	)

def emailIsUnique(email):
	db = createMongoConnection()
	user_collection = db.auth_user
	userObject = loads(dumps(user_collection.find({"username": email})))
	if (len(userObject) > 0):
		return False
	return True

def firstNameIsValid(firstName):
	if (len(firstName) == 0):
		return False
	return True

def passwordIsValid(password):
	if (len(password) < 6):
		return False
	return True

def registerUserHelper(request):
	firstName = request.POST.get('firstName')
	lastName = request.POST.get('lastName')
	email = request.POST.get('email')
	password = request.POST.get('password')
	if (emailIsUnique(email)):
		if (firstNameIsValid(firstName)):
			if (passwordIsValid(password)):
				createUser(firstName, lastName, email, password)
				encoded = base64.b64encode(email, "utf-8")
				encoded = encoded.decode("utf-8")
				accountVerificationLink = settings.DOMAIN_NAME + "/verify-user-account?user=" + encoded
				sendMail(email, settings.SENDGRID_SENDFROM, "Account Verification Request || Decora Systems", accountVerificationLink)
				message = "Account creation successfull !"
				status = 0
			else:
				message = "Password is less than 6 characters in length !"
				status = 1
		else:
			message = "First Name cannot be empty !"
			status = 2
	else:
		message = "This email already exists !"
		status = 3
	return {
		"message": message,
		"status": status
	}	

def register(request):
	if (request.method == "GET"):
		context = RequestContext(request, {'request': request, 'user': request.user})
		
		return render_to_response("user-register.html", context_instance=context)
	elif (request.method == "POST"):
		responseObject = registerUserHelper(request)
		if (responseObject.status == 0):
			if 'avatar' in request.FILES.keys():
				client = MongoClient()
				db = client[settings.DATABASE_NAME]

				avatar = request.FILES['avatar']

				updateUserAvatar(avatar, db, email)
			return HttpResponseRedirect('/admin')

		return render(request, 'user-register.html', {"message": message})

@csrf_exempt
def signupAPI(request):
	if (request.method == "GET"):
		return HttpResponseForbidden()
	else:
		responseObject = registerUserHelper(request)
		return HttpResponse(
			json.dumps(responseObject), content_type="application/json")

@csrf_exempt
def loginAPI(request):
	if (request.method == "GET"):
		return HttpResponseForbidden()
	else:
		email = request.POST.get('email')
		password = request.POST.get('password')

		user = auth.authenticate(username = email, password = password)
		userId = None
		if (user is not None):
			if (user.is_active):
				auth.login(request, user)
				message = SUCCESSFUL_LOGIN_MESSAGE
				status = 0
			else:
				message = UNAUTHORIZED_LOGIN_MESSAGE
				status = 1
			userId = user.id
		else:
			message = AUTHENTICATION_ERROR_MESSAGE
			status = 2
		return HttpResponse(
			json.dumps(
				{
					"status": status,
					"message": message,
					"userId": userId
				}), content_type="application/json")


def verifyUserAccount(request):
	userId = request.GET.get("user")
	email = base64.b64decode(userId)
	email = email.decode("utf-8")
	db = createMongoConnection()
	user_collection = db.auth_user
	userObject = loads(dumps(user_collection.find({"username": email})))
	if (len(userObject) == 0):
		raise Http404
	else:
		user_collection.update({"username": email}, {"$set": {"is_active": True}}, upsert = False)
		message = "Account has been verified successfully !"
		return render(request, "user-verification-success.html")


def forgotPassword(request):
	if (request.method == "GET"):
		return render(request, "user-forgot-password.html")
	elif (request.method == "POST"):
		email = request.POST.get("email")
		print(email)
		db = createMongoConnection()
		user_collection = db.auth_user
		userObject = loads(dumps(user_collection.find({"username": email})))
		if (len(userObject) == 0):
			message = "This user does not exist !"
		else:
			encoded = base64.b64encode(email, "utf-8")
			encoded = encoded.decode("utf-8")
			resetPasswordLink = settings.DOMAIN_NAME + "/reset-password?user=" + encoded
			sendMail(email, settings.SENDGRID_SENDFROM, "Forgot password request || Decora Systems", resetPasswordLink)
			message = "An email has been sent to you with reset password link."
		return render(request, "user-forgot-password.html", {"message": message})

def resetPasswordHelper(password, user):
	user.set_password(password)
	user.save()

def resetPassword(request):
	if (request.method == "GET"):
		if (request.GET.get("user") is None):
			if (request.user.is_authenticated()):
				return render(request, "user-reset-password.html")
			else:
				raise Http404
		else:
			userId = request.GET.get("user")
			email = base64.b64decode(userId)
			email = email.decode("utf-8")
			db = createMongoConnection()
			user_collection = db.auth_user
			userObject = loads(dumps(user_collection.find({"username": email})))
			if (len(userObject) == 0):
				raise Http404
			else:
				return render(request, "user-reset-password.html", {"userId": userId})
	elif(request.method == "POST"):
		if (request.GET.get("user") is None):
			if (request.user.is_authenticated()):
				user = request.user
				password = request.POST.get("password")
				if (len(password) >= 6):
					resetPasswordHelper(password, user)
					logout(request)
					return render(request, "user-reset-password-success.html")
				else:
					message = "Password length is less than 6 characters !"
					return render(request, "user-reset-password.html", {"message": message})
			else:
				return HttpResponseRedirect("/admin")
		else:
			userId = request.POST.get("userId")
			email = base64.b64decode(userId)
			email = email.decode("utf-8")
			db = createMongoConnection()
			user_collection = db.auth_user
			userObject = loads(dumps(user_collection.find({"username": email})))
			if (len(userObject) == 0):
				raise Http404
			else:
				print(email)
				user = User.objects.get(username = email)
				print(user)
				password = request.POST.get("password")
				if (len(password) >= 6):
					resetPasswordHelper(password, user)
					logout(request)
					return render(request, "user-reset-password-success.html")
				else:
					message = "Password length is less than 6 characters !"
					return render(request, "user-reset-password.html?user=" + userId, {"message": message})

@csrf_exempt
def fileUploadAPI(request):
	if request.method == "POST":
		uploadedFile = request.FILES['file']
		print(type(uploadedFile))
		block_blob_service = createAzureBlobService()
		tempFile = tempfile.TemporaryFile()
		isUnique = False
		counter = 0
		while (counter < 15):
			try:
				fileName = uploadedFile.name + str(generate16DigitRandomNumber())
				block_blob_service.get_blob_to_stream(settings.AZURE_CONTAINER_NAME, fileName, tempFile)
			except Exception, e:
				writeFileToAzureFromRequest(uploadedFile, fileName)
				isUnique = True
				break
				print(e)
			counter += 1
		if (not isUnique):
			message = "There is some error, please try again later !"
			return HttpResponse(json.dumps({
					"message": message,
					"status": 0
				}), content_type = "application/json")
		else:
			return HttpResponse(json.dumps({
					"FileName": fileName, 
					"status": 1
				}), content_type = "application/json")
	else:
		raise Http404

def checkHasAssetName(assetName):
	if (len(assetName) == 0):
		return False
	return True

def checkHasAssetType(assetType):
	if (len(assetType) == 0):
		return False
	return True

def checkHasFileUploaded(fileName):
	block_blob_service = createAzureBlobService()
	tempFile = tempfile.TemporaryFile()
	try:
		block_blob_service.get_blob_to_stream(settings.AZURE_CONTAINER_NAME, fileName, tempFile)
	except Exception, e:
		print(e)
		return False
	return True

@csrf_exempt
def addAssetAPI(request):
	if request.method == "POST":
		assetName = request.POST.get("AssetName")
		assetType = request.POST.get("AssetType")
		fileName = request.POST.get("FileName")

		if checkHasAssetName(assetName):
			if checkHasAssetType(assetType):
				if checkHasFileUploaded(fileName):
					db = createMongoConnection()
					assetCollection = db.assets
					assetId = assetCollection.insert({
						"assetName": assetName,
						"assetType": assetType,
						"fileName": fileName
					})
					message = "Success"
				else:
					message = "There is no file with this file name !"
			else:
				message = "Asset type cannot be empty !"
		else:
			message = "Asset name cannot be empty !"
		return HttpResponse(json.dumps({"message": message}), content_type="application/json")
	else:
		raise Http404