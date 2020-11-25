import React from 'react';
import PropTypes from 'prop-types';

const DeleteButton = ({ onDelete, icon = 'delete' }) => (
    <button type="button" className="btn btn--delete" onClick={onDelete}>
        <i className="material-icons">{icon}</i>
    </button>
);

DeleteButton.propTypes = {
    onDelete: PropTypes.func.isRequired,
    icon: PropTypes.string,
};

export default DeleteButton;
