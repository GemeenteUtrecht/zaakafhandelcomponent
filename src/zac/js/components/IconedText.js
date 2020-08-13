import React from 'react';
import PropTypes from 'prop-types';


const IconedText = ({ icon, children }) => {
    return (
        <span className="iconed-text">
            <i className="material-icons iconed-text__icon">{icon}</i>
            {children}
        </span>
    );
};

IconedText.propTypes = {
    icon: PropTypes.string.isRequired,
    children: PropTypes.node,
};


export { IconedText };
