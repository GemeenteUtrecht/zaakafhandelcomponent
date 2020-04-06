const fetchDefaults = {
    credentials: 'same-origin',  // required for Firefox 60, which is used in werkplekken
};

const apiCall = (url, opts) => {
    const options = Object.assign({}, fetchDefaults, opts);
    return window.fetch(url, options);
};


export { apiCall };
