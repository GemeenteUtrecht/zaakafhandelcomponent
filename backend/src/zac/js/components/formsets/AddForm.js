import React from 'react';
import PropTypes from 'prop-types';

const AddForm = ({ onAdd, children = 'Nog één toevoegen', icon = 'add_circle' }) => (
    <button type="button" className="btn" onClick={onAdd}>
        { icon ? <i className="material-icons">{icon}</i> : null }
        { children }
    </button>
);

AddForm.propTypes = {
    onAdd: PropTypes.func.isRequired,
    children: PropTypes.node,
    icon: PropTypes.string,
};

export { AddForm };
