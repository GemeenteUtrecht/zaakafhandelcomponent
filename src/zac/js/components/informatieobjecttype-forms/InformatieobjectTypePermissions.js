import React from 'react';
import PropTypes from 'prop-types';
import { useAsync } from 'react-use';
import { useImmerReducer } from 'use-immer';

import {get} from '../../utils/fetch';
import {Select} from '../forms/Select';
import {FormSet} from '../formsets/FormSet';

import InformatieobjecttypePermissionForm from './InformatieobjecttypePermissionForm';
import PermissionsToDelete from './PermissionsToDelete';


const initialState = {
    catalogus: '',
    informatieobjecttypen: [],
};


const reducer = (draft, action) => {
    switch (action.type) {
        case 'CATALOGUE_SELECTED': {
            draft.catalogus = action.payload;
            break;
        }
        case 'INFORMATIEOBJECTTYPEN_LOADED': {
            draft.informatieobjecttypen = action.payload;
            break;
        }
        default:
            throw new Error(`Unknown action ${action.type}`);
    }
}


const InformatieobjectTypePermissions = ({ configuration, catalogChoices, existingFormData }) => {
    if (existingFormData.length) {
        initialState.catalogus = existingFormData[0].catalogus;
    }

    const [
        {catalogus, informatieobjecttypen},
        dispatch
    ] = useImmerReducer(reducer, initialState);

    const loadInformatieobjecttypen = async () => {
        if (!catalogus) {
            return [];
        }
        const informatieobjecttypen = await get('/accounts/api/informatieobjecttypen', {catalogus: catalogus});
        dispatch({
            type: 'INFORMATIEOBJECTTYPEN_LOADED',
            payload: informatieobjecttypen.emptyFormData.map(fd => fd.omschrijving),
        });
    };

    useAsync(
        loadInformatieobjecttypen,
        [catalogus]
    );

    const getFormData = () => {
        const formData = existingFormData.map(fd => {
            if (fd.catalogus === catalogus) {
                return fd;
            } else {
                // different catalogue -> mark for delete by un-selecting
                return {...fd, forceDelete: true};
            }
        });
        const existingOmschrijving = new Set(formData.map(fd => fd.omschrijving));
        const extra = informatieobjecttypen
            .filter(omschrijving => !existingOmschrijving.has(omschrijving))
            .map(omschrijving => ({
                id: '',
                catalogus: catalogus,
                omschrijving: omschrijving,
                max_va: 'openbaar',
                selected: false,
            }));

        return formData.concat(extra);
    };

    const formData = getFormData();

    return (
        <>
             <Select
                name="_iot_catalogus"
                id="id__iot_catalogus"
                label="Catalogus"
                helpText="Informatieobjecttypencatalogus waarin de documenttypen voorkomen"
                choices={catalogChoices}
                value={catalogus}
                onChange={(event) => dispatch({type: 'CATALOGUE_SELECTED', payload: event.target.value})}
            />

            <h4>Selecteer de relevante informatieobjecttypen</h4>
            { formData.length ? null : 'Geen informatieobjecttypen gevonden in deze catalogus.' }

            <FormSet
                configuration={configuration}
                renderForm={InformatieobjecttypePermissionForm}
                renderAdd={null}
                formData={formData}
            />

            {/* visualize the permissions to drop */}
            <PermissionsToDelete catalogus={catalogus} existingFormData={existingFormData} />
        </>
    );
};

InformatieobjectTypePermissions.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        extra: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    catalogChoices: PropTypes.arrayOf(PropTypes.array).isRequired,
    existingFormData: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        catalogus: PropTypes.string.isRequired,
        omschrijving: PropTypes.string.isRequired,
        max_va: PropTypes.string.isRequired,
        selected: PropTypes.bool.isRequired,
    })),
};


export default InformatieobjectTypePermissions;
