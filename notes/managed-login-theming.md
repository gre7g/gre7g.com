WARNING: The following exchange is with AIR and has not been reviewed by a human.

### User

i'm using aws managed login. i believe that allows you to theme the cognito login page to be consistent with the site design. you can create "theming information" and add it to your aws sam template, but i don't understand how. do you know how to do that?

### Assistant

Yes. Your `template.yaml` already has a `LoginBranding` resource linked to your Cognito app client; it currently requests Cognito’s default appearance.

To customize it, change `UseCognitoProvidedValues` to `false` and add `Settings`. For example, this uses colors from `static/styles.css`:

```yaml
  LoginBranding:
    Type: AWS::Cognito::ManagedLoginBranding
    DeletionPolicy: !If [DeletionProtectionEnabled, Retain, Delete]
    UpdateReplacePolicy: !If [DeletionProtectionEnabled, Retain, Delete]
    Properties:
      UserPoolId: !Ref UserPool
      ClientId: !Ref UserPoolClient
      UseCognitoProvidedValues: false
      Settings:
        categories:
          global:
            colorSchemeMode: LIGHT
        components:
          pageBackground:
            lightMode:
              color: "f7f1e5ff"
          form:
            lightMode:
              backgroundColor: "fffdf8ff"
          pageText:
            lightMode:
              bodyColor: "382d25ff"
              headingColor: "382d25ff"
          primaryButton:
            lightMode:
              defaults:
                backgroundColor: "382d25ff"
                textColor: "fffaf0ff"
```

This is a starting point, not a tested deployment. Cognito colors use eight hex digits: red, green, blue, and opacity. Cognito hosts the page, so your site’s stylesheet doesn’t apply directly.

Also, your `UserPoolDomain` doesn’t specify a branding version. For the newer managed-login editor, add this under its existing `Properties`:

```yaml
      ManagedLoginVersion: 2
```

The deployed domain might already be version `2`; I can’t tell from the template alone. Version `1` is the classic hosted UI. Your pool’s `ESSENTIALS` tier supports managed login.

### Using the visual editor

You can design the page in Cognito’s managed-login branding editor, then retrieve the complete settings for your existing app client:

```powershell
aws cognito-idp describe-managed-login-branding-by-client `
  --user-pool-id 'YOUR_POOL_ID' `
  --client-id 'YOUR_CLIENT_ID' `
  --region 'YOUR_REGION' `
  --return-merged-resources `
  --output json
```

Copy the returned `ManagedLoginBranding.Settings` object into the resource’s `Settings`; images belong in the separate `Assets` property. Images such as `gre7g.png` must be supplied as encoded asset data, not merely a local path. For a larger theme, [`AWS::Include`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/transform-aws-include.html) can keep the settings in a separate file.

Console edits are useful for experimenting, but they can drift from the template. Put the final settings in the template before deploying so the template remains the source of truth. AWS documents the [branding editor](https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login-brandingeditor.html) and the [CloudFormation resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-cognito-managedloginbranding.html) in more detail.

I haven’t changed or deployed anything.