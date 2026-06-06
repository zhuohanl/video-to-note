param location string
param namePrefix string
param identityId string
param identityClientId string
param keyVaultUri string
param serviceBusNamespace string
param serviceBusQueueName string
param storageAccountName string
param appInsightsConnectionString string
param azureOpenAiEndpoint string
param azureSpeechEndpoint string
param azureVisionEndpoint string
param containerImageTag string
param tags object

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-aca'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

var commonEnv = [
  {
    name: 'APP_PROFILE'
    value: 'azure'
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: identityClientId
  }
  {
    name: 'AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE'
    value: '${serviceBusNamespace}.servicebus.windows.net'
  }
  {
    name: 'AZURE_SERVICE_BUS_QUEUE_NAME'
    value: serviceBusQueueName
  }
  {
    name: 'AZURE_STORAGE_ACCOUNT_NAME'
    value: storageAccountName
  }
  {
    name: 'AZURE_OPENAI_ENDPOINT'
    value: azureOpenAiEndpoint
  }
  {
    name: 'AZURE_SPEECH_ENDPOINT'
    value: azureSpeechEndpoint
  }
  {
    name: 'AZURE_VISION_ENDPOINT'
    value: azureVisionEndpoint
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
]

var apiWorkerEnv = concat(commonEnv, [
  {
    name: 'DATABASE_URL'
    secretRef: 'database-url'
  }
  {
    name: 'VTN_USERNAME'
    secretRef: 'vtn-username'
  }
  {
    name: 'VTN_PASSWORD_HASH'
    secretRef: 'vtn-password-hash'
  }
  {
    name: 'VTN_COOKIE_SECRET'
    secretRef: 'vtn-cookie-secret'
  }
])

var keyVaultSecrets = [
  {
    name: 'database-url'
    identity: identityId
    keyVaultUrl: '${keyVaultUri}secrets/database-url'
  }
  {
    name: 'vtn-username'
    identity: identityId
    keyVaultUrl: '${keyVaultUri}secrets/vtn-username'
  }
  {
    name: 'vtn-password-hash'
    identity: identityId
    keyVaultUrl: '${keyVaultUri}secrets/vtn-password-hash'
  }
  {
    name: 'vtn-cookie-secret'
    identity: identityId
    keyVaultUrl: '${keyVaultUri}secrets/vtn-cookie-secret'
  }
]

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      secrets: keyVaultSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'vtn-api:${containerImageTag}'
          env: apiWorkerEnv
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-web'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'web'
          image: 'vtn-web:${containerImageTag}'
          env: [
            {
              name: 'NEXT_PUBLIC_API_BASE_URL'
              value: 'https://${apiApp.properties.configuration.ingress.fqdn}'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource workerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${namePrefix}-worker'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: keyVaultSecrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: 'vtn-worker:${containerImageTag}'
          env: apiWorkerEnv
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
    }
  }
}

output apiUrl string = 'https://${apiApp.properties.configuration.ingress.fqdn}'
output webUrl string = 'https://${webApp.properties.configuration.ingress.fqdn}'
