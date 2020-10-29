import React from 'react';

const CsrfTokenContext = React.createContext(null);
CsrfTokenContext.displayName = 'CsrfTokenContext';

const TitleContext = React.createContext(null);
TitleContext.displayName = 'TitleContext';

export { CsrfTokenContext, TitleContext };
