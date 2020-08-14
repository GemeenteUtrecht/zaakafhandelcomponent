import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import { useAsync } from 'react-use';
import { useImmerReducer } from "use-immer";

import { apiCall, get } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { FileInput } from '../forms/Inputs';
import { Select } from '../forms/Select';
import { SubmitRow } from '../forms/Utils';


const ENDPOINT_UPLOAD = '/core/api/documents/upload';
const ENDPOINT_GET_ZIO = '/core/api/documents/get-informatieobjecttypen';


const initialState = {
    informatieobjecttype: {
        value: '',
        errors: [],
    },
    file: {
        value: null,
        errors: [],
    },
};


function reducer(draft, action) {
    switch (action.type) {
        case 'RESET':
            return initialState;

        case 'FIELD_CHANGED': {
            const { name, value } = action.payload;
            draft[name].value = value;
            draft[name].errors = [];
            break;
        }

        case 'FILE_SELECTED': {
            draft.file.value = action.payload || null;
            draft.file.errors = [];
            break;
        }

        case 'VALIDATION_ERRORS': {
            const errors = action.payload;
            for (const [field, errors] of Object.entries(errors)) {
                draft[field].errors = errors;
            }
            break;
        }

        default:
            break;
    }
}


const uploadFile = async (csrftoken, informatieobjecttype, file, zaak) => {
    // prepare multipart file upload
    const data = new FormData();
    data.append('csrfmiddlewaretoken', csrftoken);
    data.append('informatieobjecttype', informatieobjecttype);
    data.append('zaak', zaak);
    data.append('file', file);

    // send the API call
    const response = await apiCall(
        ENDPOINT_UPLOAD,
        {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
            },
            body: data,
        }
    );
    console.log(response.ok);
    const responseData = await response.json();
    console.log(responseData);
};


const AddDocument = ({ zaakUrl, endpoint='/api/documents/upload', inModal=false }) => {
    const csrftoken = useContext(CsrfTokenContext);
    const [state, dispatch] = useImmerReducer(reducer, initialState);

    const onFieldChange = (event) => {
        const { name, value } = event.target;
        dispatch({
            type: 'FIELD_CHANGED',
            payload: {
                name,
                value
            }
        });
    };

    const onSubmit = async (event) => {
        event.preventDefault();
        const uploadResult = await uploadFile(
            csrftoken,
            state.informatieobjecttype.value,
            state.file.value,
            zaakUrl,
        );
        console.log(uploadResult);
    };

    const { loading, value } = useAsync(
        async () => await getInformatieObjectTypen(zaakUrl),
        [zaakUrl]
    );

    if (loading) {
        return (<span className="loader" />);
    }

    return (
        <form onSubmit={ onSubmit } className={ inModal ? 'form form--modal' : 'form' }>
            <Select
                name="informatieobjecttype"
                label="Documenttype"
                choices={ value.map( iot => [iot.url, iot.omschrijving] ) }
                id="id_informatieobjecttype"
                helpText="Kies een relevant documenttype. Je ziet de documenttypes die bij het zaaktype horen."
                onChange={ onFieldChange }
                value={ state.informatieobjecttype.value }
                errors={ state.informatieobjecttype.errors }
                required
            />

            <FileInput
                name="document"
                label="Bladeren"
                id="id_document"
                helpText="Selecteer het document."
                onChange={ files => dispatch({
                    type: 'FILE_SELECTED',
                    payload: files[0],
                }) }
                errors={ state.file.errors }
                required
            >
                { state.file.value ? <em>{state.file.value.name}</em> : null }
            </FileInput>

            <div className="modal__submitrow">
                <SubmitRow text="Toevoegen" />
            </div>
        </form>
    );
};

AddDocument.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    endpoint: PropTypes.string,
};


const getInformatieObjectTypen = async (zaakUrl) => {
    const url = `${ENDPOINT_GET_ZIO}?zaak=${encodeURI(zaakUrl)}`;
    const ioTypen = await get(url);
    return ioTypen;
};


export { AddDocument };
