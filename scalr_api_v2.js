
var crypto = require('crypto');
var format = require('string-format');
var fs = require('fs');
var request = require('request');

function scalrRequestAuthentication (keyId, keySecret, method, path, params, body, date) {
    return {
        'X-Scalr-Key-Id': keyId,
        'X-Scalr-Signature': scalrSignatureAlgorithm(keySecret, scalrCanonicalRequest(method, date, path, params, body)),
        'X-Scalr-Date': date,
        'X-Scalr-Debug': 1
    }
}

function scalrSignatureAlgorithm (keySecret, canonReq) {
    return format('V1-HMAC-SHA256 {}', crypto.createHmac('sha256', keySecret).update(canonReq).digest('base64'));
}

function scalrCanonicalRequest (method, date, path, params, body) {
    return [method, date, path, params, body].join('\n');
}

function scalrAPICall (creds, path, method, params, body, date, callback) {
    request.get({
        url: creds.api_url + path,
        headers: scalrRequestAuthentication(
                    creds.api_key_id, creds.api_key_secret,
                    method, path, params, body, date
                ),
        json: true
    }, function(error, response, body) {
        if (error) {
            callback(error, http);
        } else {
            callback(null, body);
        };
    });
}

var config = process.argv[1].replace(/\.js$/, '.json');
if (fs.existsSync(config)) {
    var date = new Date().toISOString();
    var creds = JSON.parse(fs.readFileSync(config).toString());
    scalrAPICall(creds, '/api/v1beta0/account/environments',
                'GET', '', '',  date, function(error, content) {
                    if (!error) {
                        console.log(content);
                    }
                });
}
