const getDownloadUrl = (template, doc) => {
    let url = template;
    for (const attr of ['bronorganisatie', 'identificatie', 'versie']) {
        url = url.replace(`_${attr}_`, doc[attr]);
    }
    return url;
};

export { getDownloadUrl };
