param location string
param namePrefix string
param managedIdentityPrincipalId string
param operatorPrincipalId string = ''
param loginUsername string
param postgresFqdn string
@secure()
param postgresAdminPassword string
@secure()
param vtnPasswordHash string
@secure()
param vtnCookieSecret string
param tags object

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take('${namePrefix}-kv', 24)
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    enablePurgeProtection: false
    enableRbacAuthorization: true
    enabledForTemplateDeployment: true
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource managedIdentitySecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, managedIdentityPrincipalId, 'key-vault-secrets-user')
  scope: vault
  properties: {
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
  }
}

resource operatorSecretsOfficer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(operatorPrincipalId)) {
  name: guid(vault.id, operatorPrincipalId, 'key-vault-secrets-officer')
  scope: vault
  properties: {
    principalId: operatorPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
  }
}

resource usernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'vtn-username'
  parent: vault
  properties: {
    value: loginUsername
  }
}

resource passwordHashSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'vtn-password-hash'
  parent: vault
  properties: {
    value: vtnPasswordHash
  }
}

resource cookieSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'vtn-cookie-secret'
  parent: vault
  properties: {
    value: vtnCookieSecret
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'database-url'
  parent: vault
  properties: {
    value: 'postgresql://vtnadmin:${postgresAdminPassword}@${postgresFqdn}:5432/vtn?sslmode=require'
  }
}

output name string = vault.name
output vaultUri string = vault.properties.vaultUri
