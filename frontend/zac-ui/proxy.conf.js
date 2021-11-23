module.exports = {
  '/alfresco': {
    target: 'https://alfresco-tezza.aks.utrechtproeftuin.nl',
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
