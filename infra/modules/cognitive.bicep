param location string
param namePrefix string
param principalId string
param tags object

var cognitiveUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-ai'
  location: location
  kind: 'AIServices'
  tags: tags
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${namePrefix}-ai'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-openai'
  location: location
  kind: 'OpenAI'
  tags: tags
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${namePrefix}-openai'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-speech'
  location: location
  kind: 'SpeechServices'
  tags: tags
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${namePrefix}-speech'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource vision 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-vision'
  location: location
  kind: 'ComputerVision'
  tags: tags
  sku: {
    name: 'S1'
  }
  properties: {
    customSubDomainName: '${namePrefix}-vision'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource aiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, principalId, 'cognitive-user')
  scope: aiServices
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveUserRole
  }
}

resource openAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, principalId, 'cognitive-user')
  scope: openAi
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveUserRole
  }
}

resource speechUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(speech.id, principalId, 'cognitive-user')
  scope: speech
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveUserRole
  }
}

resource visionUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vision.id, principalId, 'cognitive-user')
  scope: vision
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveUserRole
  }
}

output aiServicesEndpoint string = aiServices.properties.endpoint
output openAiEndpoint string = openAi.properties.endpoint
output speechEndpoint string = speech.properties.endpoint
output visionEndpoint string = vision.properties.endpoint
