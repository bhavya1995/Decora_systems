"""decora URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Add an import:  from blog import urls as blog_urls
	2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings

from decora.views import home, logout, register, forgotPassword, resetPassword, signupAPI, verifyUserAccount, loginAPI, fileUploadAPI, addAssetAPI

urlpatterns = [
	# url(r'^admin/', include(admin.site.urls)),
	url('', include('social.apps.django_app.urls', namespace='social')),
	url('', include('django.contrib.auth.urls', namespace='auth')),
	url(r'^admin/', include('admin_panel.urls')),
	url(r'^$', home),
	url(r'^logout$', logout),
	url(r'^register$', register),
	url(r'^forgot-password$', forgotPassword),
	url(r'^reset-password$', resetPassword),
	url(r'^signup-api$', signupAPI),
	url(r'^verify-user-account$', verifyUserAccount),
	url(r'^login-api$', loginAPI),
	url(r'^fileUpload-api$', fileUploadAPI),
	url(r'^addAsset-api$', addAssetAPI),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

