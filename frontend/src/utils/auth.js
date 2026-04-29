export const isEndpointAllowed = (endpoint_ref, currentRole, authRules = []) => {
  if (!currentRole || !endpoint_ref) return false;
  
  // Find the auth rule matching the current role (case-insensitive)
  const rule = authRules.find(r => 
    r.role && r.role.toLowerCase() === currentRole.toLowerCase()
  );

  // If no rule is found for this role, default to denied
  if (!rule) return false;

  // Check if the endpoint is in the allowed list
  const allowedEndpoints = rule.allowed_endpoints || [];
  return allowedEndpoints.includes(endpoint_ref);
};
