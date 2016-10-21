import pymongo
import json
import gridfs

from django.shortcuts import render

from django.http import HttpResponseRedirect
from django.http import HttpResponse, Http404

from django.contrib import auth
from django.contrib.auth.models import User
from django.conf import settings

from pymongo import MongoClient

from bson.json_util import dumps
from bson.objectid import ObjectId

# Create your views here.

def home(request):
	client = MongoClient()
	db = client[settings.DATABASE_NAME]
	organizationCollection = db.organization
	data = organizationCollection.find()
	print(dumps(data))
	return render(request, 'home.html', data)

def logout(request):
	auth.logout(request)
	return HttpResponseRedirect('/admin')

def createUser(firstName, lastName, email, password):
	user = User.objects.create(
		username = email, first_name = firstName, 
		last_name = lastName, is_active = True, email = email
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

def register(request):
	if (request.method == "GET"):
		return render(request, "user-register.html")
	elif (request.method == "POST"):
		firstName = request.POST.get('firstName')
		lastName = request.POST.get('lastName')
		email = request.POST.get('email')
		password = request.POST.get('password')

		if (len(firstName) != 0 and len(email) != 0 and len(password) != 0 and len(password) >= 6):
			createUser(firstName, lastName, email, password)
			user = auth.authenticate(username = email, password = password)
			auth.login(request,user)

			if 'avatar' in request.FILES.keys():
				client = MongoClient()
				db = client[settings.DATABASE_NAME]

				avatar = request.FILES['avatar']

				updateUserAvatar(avatar, db, email)
			return HttpResponseRedirect('/admin')
		elif(len(firstName) == 0):
			message = "First Name cannot be empty !"
		elif(len(email) == 0):
			message = "Email ID cannot be empty !"
		elif(len(password) == 0):
			message = "Password cannot be empty !"
		elif(len(password) < 6):
			message = "Password cannot be less than 6 characters !"

		return render(request, 'user-register.html', {"message": message})

def forgotPassword(request):
	if (request.method == "GET"):
		return render(request, "user-forgot-password.html")
	elif (request.method == "POST"):
		email = request.POST.get("email")

