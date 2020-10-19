import React from 'react';
import PropTypes from 'prop-types';

import { AddForm } from '../formsets/AddForm';

const AddStep = ({ onAdd }) => (
    <div className="validsign-signer-add" style={{ marginTop: '1rem' }}>
        <AddForm onAdd={onAdd}>
            Extra stap toevoegen
        </AddForm>
    </div>
);

AddStep.propTypes = {
    onAdd: PropTypes.func.isRequired,
};

export default AddStep;
