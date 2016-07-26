# API Tools

<!--
---

## Amazon Cloud Drive

Consumer version of the AWS S3: Simple Storage Service, which has a separate API than boto.
https://developer.amazon.com/public/apis/experience/cloud-drive

Currently WORK IN PROGRESS...

PreRequisites:
* Register your profile here: https://developer.amazon.com/lwa/sp/overview.html
* Whitelist your app here: https://developer.amazon.com/cd/sp/overview.html
* Store API Key in amazon_keys.py using amazon_keys.py.sample guidelines
* Scripts requires python modules: pip install boto

$ python amazon_cloud_tool.py

-->
---

## Yahoo! flickr

Manipulate collections, photosets (albums) and photos using the flickr API:
https://www.flickr.com/services/api/

Updated to using oauth2 method, since frob method deprecated for uploading images:
https://www.flickr.com/services/api/auth.oauth.html

PreRequisites:
* Request API Key for tool here: https://www.flickr.com/services/apps/create/
* Store API Key in flickr_keys.py using flickr_keys.py.sample guidelines
* Scripts requires python modules: pip install lxml oauth2 requests

$ python flickr_oauth_tool.py

---

## Scalr v2

Use the Scalr v2 API, which now supports JSON, to display all the environments

PreRequisites:
* Request API key id/secret from you company site: https://scalr.company.com/#/core/api2
* Update scalr_api_v2.json with obtained values
* Modify the script to handle addition paths (https://api-explorer.scalr.com/)

---

