import React from 'react';
import PropTypes from 'prop-types';

import { AddForm } from '../formsets/AddForm';


const AddRow = ({ onAdd }) => {
    return (
        <div className="validsign-signer-add">
            <AddForm onAdd={ onAdd }>
                Extra ondertekenaar toevoegen
            </AddForm>
        </div>
    );
};

AddRow.propTypes = {
    onAdd: PropTypes.func.isRequired,
};


export { AddRow };
