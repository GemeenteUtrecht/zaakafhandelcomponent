import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';


const AddActivityButton = ({ portalNode }) => {
    const btn = (
        <button type="button" className="btn btn--control btn--control-focus">
            <i className="material-icons">add</i>
            Activiteit toevoegen
        </button>
    );
    return ReactDOM.createPortal(btn, portalNode);
};

AddActivityButton.propTypes = {
    portalNode: PropTypes.object.isRequired,
};


export { AddActivityButton };
