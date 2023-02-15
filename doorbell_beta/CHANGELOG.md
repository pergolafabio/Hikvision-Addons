# Changelog

## 3.0.0.beta

This is the first of the releases made available under the Beta channel. Expect some small issues while we iron out the last bugs and get ready for an exiting official release. You feedback is very welcome! If you have any doubt, would like to report a bug or to simply chime in, please have a look at the [Github Issues page](https://github.com/pergolafabio/Hikvision-Addons/issues) and drop us a note!

The addon has been completely overhauled, with lots of new features and an improved codebase that will aid future integrations/improvements.
Some of the biggest improvements are:
- Ability to handle multiple doorbells
    - Automatic discovery of doorbell type (indoor or outdoor) upon connection
- Ability to run the addon as a standalone Docker container, for Home Assistant installation without _supervisor_.
    - Load configuration from a JSON/YAML file or from environment variables
- Configurable system logs
- New beta channel to test pre-release versions of the addon
- Automated testing using Github Actions
- Improved documentation for both end users and developers