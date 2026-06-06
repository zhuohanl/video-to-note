param location string
@minLength(3)
param namePrefix string
param principalId string
param tags object

var accountName = 'st${uniqueString(resourceGroup().id, namePrefix)}'
var blobContainers = [
  'proxy'
  'frames'
  'exports'
  'examples'
]

resource account 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: account
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for containerName in blobContainers: {
  name: containerName
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}]

resource blobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, 'storage-blob-data-contributor')
  scope: account
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

output accountName string = account.name
output blobEndpoint string = account.properties.primaryEndpoints.blob
