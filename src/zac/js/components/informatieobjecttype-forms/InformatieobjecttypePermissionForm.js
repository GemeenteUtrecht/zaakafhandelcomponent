import React, {useContext, useState} from 'react';
import PropTypes from 'prop-types';

import {CheckboxInput, HiddenInput} from "../forms/Inputs";
import { PrefixContext } from '../formsets/context';
import {Select} from '../forms/Select';
import { VERTROUWELIJKHEIDAANDUIDINGEN } from '../../constants';


const InformatieobjecttypePermissionForm = ({
    index,
    data: {id, max_va, catalogus, omschrijving, selected}
}) => {
    const [checked, setChecked] = useState(selected);
    const prefix = useContext(PrefixContext);

    const prefixedId = `${prefix}-id_selected`;

    return (
        <div className="form__field-group">
            <HiddenInput name='omschrijving' id='id_omschrijving' value={ omschrijving } />
            <HiddenInput name='id' id='id_id' value={ id } />
            <HiddenInput name='catalogus' id='id_catalogus' value={ catalogus } />
            <CheckboxInput
                name='selected'
                id={'id_selected'}
                checked={checked}
                initial={checked}
                value={checked}
                onChange={(event) => setChecked(event.target.checked)}
            />
            <label htmlFor={prefixedId}>{omschrijving}</label>
            <Select
                name={'max_va'}
                id={'id_max_va'}
                choices={VERTROUWELIJKHEIDAANDUIDINGEN}
                initial={max_va || VERTROUWELIJKHEIDAANDUIDINGEN[0][0]}
            />
            <CheckboxInput
                name="DELETE"
                checked={!checked}
                value="true"
                style={{display: 'none'}}
            />
        </div>
    );
};

InformatieobjecttypePermissionForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.shape({
        id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
        catalogus: PropTypes.string.isRequired,
        omschrijving: PropTypes.string.isRequired,
        max_va: PropTypes.string.isRequired,
        selected: PropTypes.bool.isRequired,
    }),
};


export default InformatieobjecttypePermissionForm;
