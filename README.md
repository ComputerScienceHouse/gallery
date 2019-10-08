# CSH Gallery

## Overview
A gallery for RIT's [Computer Science House](https://csh.rit.edu), made to replace an instance of [Gallery 2](http://galleryproject.org/). CSH Members can read more about it on our [internal wiki page](https://wiki.csh.rit.edu/wiki/Gallery). CSH Gallery is built using Flask, and hosted on our OpenShift Origin cluster. It allows for uploading of many different common filetypes, and is easily extensible for any new ones that members may want to upload in the future.

## Screenshots
CSH Gallery is an internal site, and thus not public-facing, however below are some screenshots showing how the site looks and works.


#### View Directory:
![View Directory](https://csh.rit.edu/~ram/gallery/gallery_dir.png)

#### View Image:
![View Image](https://csh.rit.edu/~ram/gallery/gallery_img.png)

#### View Text File:
![View Text File](https://csh.rit.edu/~ram/gallery/gallery_txt.png)

## Installation on Openshift Origin
CSH Gallery is designed with Openshift Origin in mind as the hosting platform.
Below are a series of instructions needed in order to get CSH Gallery running on
an Openshift Origin cluster.

1. Create a new Python3.5 Source to Image Openshift Project

2. Point Openshift towards your forked CSH Gallery Repository and setup build
   hooks and routing as you see appropriate

3. Under the builds menu select your BuildConfig and then go to Actions -> Edit
   Build Configuration

   a. Under Image Configuration please change Build From to "Docker Image"
   b. Under Image Configuration please change Docker Image Repository to
   "liammiddlebrook/s2i-python-container"

4. Under the Deployments menu select your DeploymentConfig and then go to the
   Environment section

   a. Enter in your OIDC provider information as follows:
   ```
   GALLERY_OIDC_CLIENT_SECRET = $yourOIDCclientSecret
   GALLERY_OIDC_ISSUER = $yourOIDCissuerURI
   ```

   b. Enter in your hosting and route information as follows:
   ```
   GALLERY_PORT = $thePortExposedByYourRoute
   GALLERY_SERVER_NAME = $theDNSRecordForAccessingYourGalleryInstance
   ```

   c. Enter in your ldap bind information as follows:
   ```
   GALLERY_LDAP_BIND_PW = $ldapBindPassword
   ```

   d. Enter in your database credential string as follows:
   ```
   GALLERY_DATABASE_URI = $yourSQLAlchemyConnectionString
   ```

   e. Enter in your S3 credentials as follows:

   ```
   GALLERY_S3_ACCESS_ID = $s3AccessID
   GALLERY_S3_BUCKET_ID = $s3BucketID
   GALLERY_S3_SECRET_KEY = $s3SecretKey
   ```

## Local Development
Below are instructions for running gallery locally. It assumes that you have already forked and cloned this repository onto your local machine.

1. Change the line in `__init__.py` that sets the config file from `config.env.py` to `localconfig.env.py`.

2. Get gallery dev secrets from an RTP and fill in `localconfig.env.py`. *DO NOT COMMIT THESE TO GIT*

3. Run `pip install -r requirements.txt`

4. Run `python3 wsgi.py`