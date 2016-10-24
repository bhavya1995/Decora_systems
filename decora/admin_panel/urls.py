from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings

from admin_panel.views import adminHome, adminLogin, viewObjects, createObject, deleteObject, viewObjectsAPI

urlpatterns = [
	url(r'^$', adminHome),
	url(r'^login$', adminLogin),
	url(r'^view-objects$', viewObjects),
	url(r'^create-object$', createObject),
	url(r'^delete-object$', deleteObject),	
	url(r'^view-objects-api$', viewObjectsAPI),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

