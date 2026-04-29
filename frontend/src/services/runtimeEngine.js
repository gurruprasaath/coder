import { callEndpoint } from './api';

export const handleAction = async (endpoint_ref, payload = {}, config = {}, runtimeId = null) => {
  console.log(`[Runtime Engine] Executing action -> ${endpoint_ref}`);
  console.log(`[Runtime Engine] Payload:`, payload);

  // 1. Validate that config exists
  if (!config) {
    console.error(`[Runtime Engine] Error: config is missing`);
    return { success: false, error: "System configuration missing" };
  }

  // 1b. Validate that config.api.endpoints exists
  if (!config.api || !config.api.endpoints) {
    console.error(`[Runtime Engine] Error: config.api.endpoints is missing`);
    return { success: false, error: "API configuration missing" };
  }

  // 5. Add debug logs: print available endpoint ids
  const availableIds = config.api.endpoints.map(e => e.id || e.name);
  console.log(`[Runtime Engine] Available endpoints:`, availableIds);

  // 2. Find endpoint
  const endpoint = config.api.endpoints.find(
    (e) => e.id === endpoint_ref || e.name === endpoint_ref
  );

  // 3. If not found:
  if (!endpoint) {
    console.error("Endpoint not found:", endpoint_ref);
    return {
      success: false,
      error: "Endpoint configuration missing"
    };
  }

  try {
    // Dispatch to the dynamic API resolver (now guaranteed to exist)
    const response = await callEndpoint(config, endpoint_ref, payload, runtimeId);
    
    console.log(`[Runtime Engine] Response from ${endpoint_ref}:`, response);
    return response;
  } catch (error) {
    // 4. Do NOT crash the app
    console.error(`[Runtime Engine] Unhandled exception executing ${endpoint_ref}:`, error);
    return { success: false, error: "Runtime execution failed" };
  }
};
