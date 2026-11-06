// Extends app.json. The Firebase config file is only referenced once it exists:
// before Firebase is set up (see "Phone push notifications" in the README) a
// missing file would make Metro log a config error on every connection.
const fs = require('fs');
const path = require('path');

module.exports = ({ config }) => {
  const hasGoogleServices = fs.existsSync(path.join(__dirname, 'google-services.json'));
  return {
    ...config,
    android: {
      ...config.android,
      ...(hasGoogleServices ? { googleServicesFile: './google-services.json' } : {}),
    },
  };
};
