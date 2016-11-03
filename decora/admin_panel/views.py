import pymongo
import json
import gridfs
import os
import tempfile

from django.shortcuts import render, redirect

from django.http import HttpResponseRedirect
from django.http import HttpResponse,Http404

from django.contrib.auth import authenticate, login

from admin_panel.utility_constants import *

from bson.json_util import dumps, loads
from bson.objectid import ObjectId

from pymongo import MongoClient

from django.conf import settings

from django.core.files.base import ContentFile

from azure.storage.blob import BlockBlobService, ContentSettings

from random import randint
from django.template.context import RequestContext
from django.shortcuts import render_to_response

# Create your views here.

def createMongoConnection():
	client = MongoClient()
	db = client[settings.DATABASE_NAME]
	return db

#view to control home page of admin
def adminHome(request):
	if (request.user.is_authenticated()):
		displayPage = "user-profile-page.html"
	else:
		displayPage = "user-login.html"
		context = RequestContext(request, {'request': request, 'user': request.user})
		return render_to_response(displayPage, context_instance=context)

	return render(request, displayPage)

#view for login of admin
def adminLogin(request):
	email = request.POST.get(EMAIL_KEY)
	password = request.POST.get(PASSWORD_KEY)
	message = EMPTY_STRING
	# Gives status of request - 1 is success and 0 is error
	status = 0

	try:
		user = authenticate(username = email, password = password)
	except:
		message = GENERAL_ERROR_MESSAGE
		status = 0
	else:
		if (user is not None):
			if (user.is_active and user.is_staff):
				login(request, user)
				message = SUCCESSFUL_LOGIN_MESSAGE
				status = 1
			else:
				message = UNAUTHORIZED_LOGIN_MESSAGE
				status = 0
		else:
			message = AUTHENTICATION_ERROR_MESSAGE
			status = 0
		return HttpResponse(
			json.dumps(
				{
					"status": status,
					 "message": message
				}), content_type="application/json")

def createAzureBlobService():
	return BlockBlobService(
		account_name=settings.AZURE_ACCOUNT_NAME,
		account_key=settings.AZURE_ACCOUNT_KEY
	)

def getImageFromBlobAndPopulateInObjectData(objectData):
	block_blob_service = createAzureBlobService()

	for o in objectData:
		o["id"] = o["_id"]
		try:
			tempFile = tempfile.TemporaryFile()
			block_blob_service.get_blob_to_stream(settings.AZURE_CONTAINER_NAME, o['thumbnail'], tempFile)
			tempFile.seek(0)
			o["image_data"] = tempFile.read().encode("base64")
			tempFile.close()
		except:
			pass
	return objectData

def viewObjectsHelper():
	db = createMongoConnection()
	objectCollection = db.objects
	objectData = loads(dumps(objectCollection.find()))
	return objectData

def viewObjects(request):
	objectData = viewObjectsHelper()
	objectData = getImageFromBlobAndPopulateInObjectData(objectData)
	return render(request, 'view-objects.html', {"objectData": objectData})

def viewObjectsAPI(request):
	objectData = viewObjectsHelper()
	for o in objectData:
		o["_id"] = str(o["_id"])
	return HttpResponse(json.dumps({"objectData": objectData}), content_type = "application/json")

def updateObjectThumbnail(thumbnail, db, objectId):
	objectCollection = db['objects']

	fs = gridfs.GridFS(db)
	file_id = fs.put(thumbnail, filename = thumbnail.name)
	objectCollection.update(
		{'_id': ObjectId(objectId)},
		{'$set': {'thumbnail_id': file_id}},
		upsert = False
	)

def generate16DigitRandomNumber():
	return randint(10**15, 10**16)

def writeFileToAzureFromRequest(requestFile, blobName):
	file_content = ContentFile( requestFile.read() )

	tempFile = tempfile.TemporaryFile()


	# Iterate through the chunks.
	for chunk in file_content.chunks():
		tempFile.write(chunk)
	tempFile.seek(0)
	block_blob_service = createAzureBlobService()
	block_blob_service.create_blob_from_stream(
		settings.AZURE_CONTAINER_NAME,
		blobName,
		tempFile
	)
	tempFile.close()


def createObject(request):
	# Render Create Object blank page
	if (request.method == "GET"  and request.GET.get("objectId") is None):
		return render(request, "create-object.html", {"hasThumbnail": False})
	
	# Render Create Object page from prefilled data
	elif(request.method == "GET"  and request.GET.get("objectId") is not None):
		objectId = request.GET.get("objectId")
		db = createMongoConnection()
		objectCollection = db.objects
		objectData = loads(dumps(objectCollection.find({"_id": ObjectId(objectId)})))
		objectData = getImageFromBlobAndPopulateInObjectData(objectData)
		if (len(objectData) > 0):
			objectData = objectData[0]
		return render(request, "create-object.html", {"data": objectData, "hasThumbnail": True})
	
	# Save data from create object page
	elif (request.method == "POST"):
		objectName = request.POST.get("objectName")
		modelId = request.POST.get("modelId")
		config = request.POST.get("config")
		objectId = request.POST.get("objectId")
		hasThumbnail = False
		if 'thumbnail' in request.FILES.keys():
			thumbnail = request.FILES['thumbnail']
		elif (objectId != ""):
			hasThumbnail = True
		else:
			objectData = {
				"name": objectName,
				"modelId": modelId,
				"config": config				
			}
			return render(request, "create-object.html", {"data": objectData, "message": EMPTY_THUMBNAIL_ERROR_MESSAGE, "hasThumbnail": False})

		db = createMongoConnection()
		objectCollection = db.objects
		while True:
			if (hasThumbnail is True):
				break
			blobName = thumbnail.name + str(generate16DigitRandomNumber())
			checkUniqueBlobName = objectCollection.find({"thumbnail": blobName})
			if (len(loads(dumps(checkUniqueBlobName))) == 0):
				break

		# Create new object
		if (objectId == ""):
			objectId = objectCollection.insert({
				"name": objectName,
				"modelId": modelId,
				"config": config,
				"thumbnail": blobName
				})

			writeFileToAzureFromRequest(thumbnail, blobName)

		# Update object without updating previous thumbnail
		elif (objectId != "" and hasThumbnail == True):
			objectData = objectCollection.update(
				{"_id": ObjectId(objectId)},
				{
					"$set": {
						"name": objectName,
						"modelId": modelId,
						"config": config,
					}
				},
				upsert = False
			)
		# Update data including thumbnail
		else:
			previousThumbnailName = objectCollection.find(
				{"_id": ObjectId(objectId)}
			)[0]["thumbnail"]
			
			objectData = objectCollection.update(
				{"_id": ObjectId(objectId)},
				{
					"$set": {
						"name": objectName,
						"modelId": modelId,
						"config": config,
						"thumbnail": blobName
					}
				},
				upsert = False
			)
			writeFileToAzureFromRequest(thumbnail, blobName)
			block_blob_service = createAzureBlobService()
			block_blob_service.delete_blob(settings.AZURE_CONTAINER_NAME, previousThumbnailName)
		return HttpResponseRedirect("/admin/view-objects")

def deleteObject(request):
	objectId = request.GET.get("objectId")
	db = createMongoConnection()
	objectCollection = db.objects
	previousThumbnailName = objectCollection.find(
		{"_id": ObjectId(objectId)}
	)[0]["thumbnail"]
	block_blob_service = createAzureBlobService()
	block_blob_service.delete_blob(settings.AZURE_CONTAINER_NAME, previousThumbnailName)
	objectCollection.remove({"_id": ObjectId(objectId)})
	
	return HttpResponseRedirect("/admin/view-objects")
