import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';


const AddActivityButton = ({ portalNode, onClick }) => {
    const btn = (
        <button
          type="button"
          className="btn btn--control btn--control-focus"
          onClick={onClick}
        >
            <i className="material-icons">add</i>
            Activiteit toevoegen
        </button>
    );
    return ReactDOM.createPortal(btn, portalNode);
};

AddActivityButton.propTypes = {
    portalNode: PropTypes.object.isRequired,
    onClick: PropTypes.func.isRequired,
};


export { AddActivityButton };
