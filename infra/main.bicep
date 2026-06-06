targetScope = 'subscription'

@minLength(2)
@maxLength(24)
param environmentName string

param location string = deployment().location
param loginUsername string = 'local'
param principalId string = ''
param resourceGroupName string = 'rg-${environmentName}'

@secure()
param postgresAdminPassword string

@secure()
param vtnPasswordHash string

@secure()
param vtnCookieSecret string

param containerImageTag string = 'latest'

var suffix = uniqueString(subscription().id, environmentName)
var namePrefix = toLower('vtn-${environmentName}-${suffix}')
var tags = {
  app: 'video-to-note-v2'
  environment: environmentName
}

resource appResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module identity 'modules/identity.bicep' = {
  name: 'identity'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    tags: tags
  }
}

module insights 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module serviceBus 'modules/servicebus.bicep' = {
  name: 'servicebus'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    administratorPassword: postgresAdminPassword
    tags: tags
  }
}

module cognitive 'modules/cognitive.bicep' = {
  name: 'cognitive'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module vault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    managedIdentityPrincipalId: identity.outputs.principalId
    operatorPrincipalId: principalId
    loginUsername: loginUsername
    postgresFqdn: postgres.outputs.fqdn
    postgresAdminPassword: postgresAdminPassword
    vtnPasswordHash: vtnPasswordHash
    vtnCookieSecret: vtnCookieSecret
    tags: tags
  }
}

module apps 'modules/apps.bicep' = {
  name: 'apps'
  scope: appResourceGroup
  params: {
    location: location
    namePrefix: namePrefix
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    keyVaultUri: vault.outputs.vaultUri
    serviceBusNamespace: serviceBus.outputs.namespaceName
    serviceBusQueueName: serviceBus.outputs.queueName
    storageAccountName: storage.outputs.accountName
    appInsightsConnectionString: insights.outputs.connectionString
    azureOpenAiEndpoint: cognitive.outputs.openAiEndpoint
    azureSpeechEndpoint: cognitive.outputs.speechEndpoint
    azureVisionEndpoint: cognitive.outputs.visionEndpoint
    containerImageTag: containerImageTag
    tags: tags
  }
}

output apiUrl string = apps.outputs.apiUrl
output webUrl string = apps.outputs.webUrl
output keyVaultName string = vault.outputs.name
output serviceBusQueueName string = serviceBus.outputs.queueName
