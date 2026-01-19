import React from 'react';

const Label = ({ label = '', required = false, idForLabel = '' }) => {
    if (!label) {
        return null;
    }

    const extraProps = {};
    if (idForLabel) {
        extraProps.htmlFor = idForLabel;
    }

    /* jshint ignore:start */
    return (
        <label className="input__label" {...extraProps}>
            { label }
            { required
                ? <span className="label label--optional">&nbsp;verplicht</span>
                : <span className="label label--optional">&nbsp;optioneel</span>}
        </label>
    );
    /* jshint ignore:end */
};

export { Label };
