import React, {useContext, useState, useEffect} from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';

import {CheckboxInput, HiddenInput} from "../forms/Inputs";
import { PrefixContext } from '../formsets/context';
import {Select} from '../forms/Select';
import { VERTROUWELIJKHEIDAANDUIDINGEN } from '../../constants';
import IconedText from '../IconedText';


const InformatieobjecttypePermissionForm = ({
    index,
    data: {id, max_va, catalogus, omschrijving, selected, forceDelete=false}
}) => {
    const [checked, setChecked] = useState(selected);
    const prefix = useContext(PrefixContext);

    const prefixedId = `${prefix}-id_selected`;

    // ensure that if the component gets re-rendered without un/re-mounting that the
    // DELETE checkbox is set if a delete is forced
    useEffect(
        () => {
            if (checked && forceDelete) {
                setChecked(false);
            } else if (!forceDelete && selected &&!checked) {
                setChecked(true);
            }
        },
        [forceDelete]
    );

    // if we're in force-delete mode, we don't display the actual forms but only use the
    // hidden inputs as part of the formsets. This ensures the formset count is up to
    // date and all the prefixes are handled correctly.
    const style = forceDelete ? {display: 'none'} : {};
    const className = classNames(
        'iot-permission',
        'grid__column grid__column--col4',
        {
            'iot-permission--enabled': checked,
            'iot-permission--force-delete': forceDelete,
        },
    );
    return (
        <div className={className}>
            <HiddenInput name="omschrijving" id="id_omschrijving" value={ omschrijving } />
            <HiddenInput name="id" id="id_id" value={ id } />
            <HiddenInput name="catalogus" id="id_catalogus" value={ catalogus } />

            <CheckboxInput
                name="selected"
                id="id_selected"
                checked={checked}
                initial={checked}
                value={checked}
                onChange={(event) => setChecked(event.target.checked)}
                style={{display: 'none'}}
            />
            <CheckboxInput
                name="DELETE"
                checked={!checked}
                value="true"
                style={{display: 'none'}}
            />

            <div className="iot-permission__icon">
                { checked ?
                    <IconedText icon="check_circle" onClick={() => setChecked(false)} />
                    : <IconedText icon="remove_circle" onClick={() => setChecked(true)} />
                 }
            </div>

            <div className="iot-permission__label">
                <label className="iot-permission__title" htmlFor={prefixedId}>
                    {omschrijving}
                </label>
                <Select
                    name="max_va"
                    id="id_max_va"
                    classes="input__control input__control--select iot-permission__va-select"
                    choices={VERTROUWELIJKHEIDAANDUIDINGEN}
                    initial={max_va || VERTROUWELIJKHEIDAANDUIDINGEN[0][0]}
                />
            </div>
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
        forceDelete: PropTypes.bool,
    }),
};


export default InformatieobjecttypePermissionForm;
