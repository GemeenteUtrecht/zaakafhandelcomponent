const fetchDefaults = {
    credentials: 'same-origin', // required for Firefox 60, which is used in werkplekken
};

const fetch = (url, opts) => {
    const options = { ...fetchDefaults, ...opts };
    return window.fetch(url, options);
};

const apiCall = fetch;

const get = async (url, params = {}, multiParams = []) => {
    let searchParams;
    if (Object.keys(params).length) {
        searchParams = new URLSearchParams(params);
    }
    if (multiParams.length > 0) {
        multiParams.map((param) => searchParams.append(
            Object.keys(param)[0], param[Object.keys(param)[0]],
        ));
    }
    url += `?${searchParams}`;
    const response = await fetch(url);
    const data = await response.json();
    return data;
};

const _unsafe = async (method = 'POST', url, csrftoken, data = {}) => {
    const opts = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify(data),
    };
    const response = await fetch(url, opts);
    const responseData = await response.json();
    return {
        ok: response.ok,
        status: response.status,
        data: responseData,
    };
};

const post = async (url, csrftoken, data = {}) => {
    const resp = await _unsafe('POST', url, csrftoken, data);
    return resp;
};

const patch = async (url, csrftoken, data = {}) => {
    const resp = await _unsafe('PATCH', url, csrftoken, data);
    return resp;
};

const put = async (url, csrftoken, data = {}) => {
    const resp = await _unsafe('PUT', url, csrftoken, data);
    return resp;
};

const destroy = async (url, csrftoken) => {
    const opts = {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrftoken,
        },
    };
    const response = await fetch(url, opts);
    if (!response.ok) {
        const responseData = await response.json();
        console.error('Delete failed', responseData);
        throw new Exception('Delete failed');
    }
};

export {
    apiCall, get, post, put, patch, destroy,
};
