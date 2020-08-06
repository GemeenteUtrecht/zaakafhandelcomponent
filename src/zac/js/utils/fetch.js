const fetchDefaults = {
    credentials: 'same-origin',  // required for Firefox 60, which is used in werkplekken
};

const apiCall = (url, opts) => {
    const options = Object.assign({}, fetchDefaults, opts);
    return window.fetch(url, options);
};


const post = async (url, csrftoken, data={}) => {
    const opts = {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify(data)
    };
    const response = await apiCall(url, opts);
    const responseData = await response.json();
    return {
        ok: response.ok,
        status: response.status,
        data: responseData,
    };
};


export { apiCall, post };
