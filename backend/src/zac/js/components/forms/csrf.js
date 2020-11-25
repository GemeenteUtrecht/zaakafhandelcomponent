import React, { useContext } from "react";

import { CsrfTokenContext } from './context';

const CsrfInput = () => {
    const csrftoken = useContext(CsrfTokenContext);
    return (
        <input type="hidden" name="csrfmiddlewaretoken" value={csrftoken} />
    );
}


export { CsrfInput };
