import React from 'react';
import PropTypes from 'prop-types';


const SignerForm = ({ index, data }) => {
    return (
        <div>
            Index: {index}
            <br/>
            Data: <pre><code>{JSON.stringify(data)}</code></pre>
        </div>
    );
};

SignerForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.object.isRequired,
};


export { SignerForm };
