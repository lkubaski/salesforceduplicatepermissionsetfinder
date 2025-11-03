# Salesforce Duplicate Permission Set Finder

A tool to find similar permission sets in a Salesforce org

Also see https://medium.com/@laurentkubaski/finding-salesforce-duplicate-permission-sets-using-the-jaccard-index-32454fa9597d

## Features

- Finds similar permission sets in a Salesforce org
- Highlights the differences between similar permission sets
- Supports system permissions, object permissions, field permissions, setup entity access permission & tab setting permissions

## Usage

```bash
python3 ./src/main.py -u username@example.com -p password -d yourdomain.demo.my -t security_token
```
## About security tokens

To generate a security token: https://help.salesforce.com/s/articleView?id=xcloud.user_security_token.htm&type=5

Note that the "Reset My Security Token" page is not visible if your org uses IP whitelisting. See https://help.salesforce.com/s/articleView?id=000386179&type=1
