const BASE_URL = "http://localhost:8000";

export const generateApp = async (prompt) => {
  console.log(`[API] generateApp called with prompt: "${prompt}"`);
  try {
    const response = await fetch(`${BASE_URL}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[API] HTTP error ${response.status}:`, errorText);
      throw new Error(`Generation failed with status ${response.status}`);
    }

    const data = await response.json();
    console.log('[API] Successfully received configuration:', data);
    return data;
  } catch (error) {
    console.error('[API] generateApp encountered an error:', error);
    throw error;
  }
};

export const fetchEvalMetrics = async () => {
  try {
    const response = await fetch(`${BASE_URL}/eval-metrics`);
    if (!response.ok) throw new Error(`Failed with status ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('[API] fetchEvalMetrics error:', error);
    return null;
  }
};

export const callEndpoint = async (config, endpoint_ref, payload = {}, runtimeId = null) => {
  try {
    // 1. Find endpoint in config.api.endpoints where name or id matches endpoint_ref
    const endpoints = config?.api?.endpoints || [];
    const endpointDef = endpoints.find(ep => ep.id === endpoint_ref || ep.name === endpoint_ref);

    if (!endpointDef) {
      console.error(`[Dynamic API] Endpoint not found in configuration: ${endpoint_ref}`);
      return { success: false, message: 'Endpoint configuration missing' };
    }

    // 2. Extract method, path, and related_table
    const { method, path, related_table } = endpointDef;
    
    let finalPath = path;
    
    // Explicit override for auth routes to hit the fixed backend auth
    if (path.includes('login') || endpoint_ref.includes('login')) {
      finalPath = '/login';
    } else if (path.includes('register') || endpoint_ref.includes('register')) {
      finalPath = '/users/register';
    }
    // Map to generic API dynamically based on related_table
    else if (related_table) {
      const isUpdateOrDelete = method.toUpperCase() === 'PUT' || method.toUpperCase() === 'DELETE';
      if (isUpdateOrDelete && payload.id) {
        finalPath = `/data/${related_table}/${payload.id}`;
      } else {
        finalPath = `/data/${related_table}`;
      }
    }
    
    console.log("Calling mapped generic API:", finalPath);

    // 3. Construct URL
    const url = `${BASE_URL}${finalPath}`;
    
    // 4. Configure fetch options
    const options = {
      method: method.toUpperCase(),
      headers: {
        'Content-Type': 'application/json',
        ...(runtimeId && { 'X-App-Id': runtimeId })
      },
    };

    // Only attach body if method is not GET/HEAD
    if (options.method !== 'GET' && options.method !== 'HEAD') {
      options.body = JSON.stringify(payload);
    }

    // 5. Execute HTTP Request
    const response = await fetch(url, options);
    
    // Parse response
    let data;
    try {
      data = await response.json();
    } catch (e) {
      data = { message: await response.text() };
    }

    if (!response.ok) {
      return { success: false, message: data.message || `Request failed with status ${response.status}`, data };
    }

    return { success: true, ...data };
  } catch (error) {
    // 6. Handle errors gracefully
    console.error(`[Dynamic API] Error executing ${endpoint_ref}:`, error);
    return { success: false, message: 'Network or execution error occurred' };
  }
};
