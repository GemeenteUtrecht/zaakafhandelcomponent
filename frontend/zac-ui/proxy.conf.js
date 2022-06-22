const ALFRESCO_DOCUMENTS_URL = '$ALFRESCO_DOCUMENTS_URL';

// Still in use?
module.exports = {
  '/alfresco': {
    target: (ALFRESCO_DOCUMENTS_URL.startsWith('$'))
      ? 'https://alfresco-tezza.aks.utrechtproeftuin.nl'
      : ALFRESCO_DOCUMENTS_URL,
    secure: false,
    changeOrigin: true,
    onProxyRes: function(proxyRes, req, res) {
      console.log('onProxyRes', proxyRes, req, res);
      const header = proxyRes.headers['www-authenticate'];
      if (header && header.startsWith('Basic')) {
        proxyRes.headers['www-authenticate'] = 'x' + header;
      }
    }
  }
};
