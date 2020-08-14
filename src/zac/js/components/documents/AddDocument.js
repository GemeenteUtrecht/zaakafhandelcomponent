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
    uploading: false,
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

        case 'UPLOAD_STARTED': {
            draft.uploading = true;
            break;
        };

        case 'UPLOAD_COMPLETED': {
            draft.uploading = false;
            break;
        };

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


const uploadFile = async (csrftoken, informatieobjecttype, file, zaak, extraDocumentFields={}) => {
    // prepare multipart file upload
    const data = new FormData();
    data.append('csrfmiddlewaretoken', csrftoken);
    data.append('informatieobjecttype', informatieobjecttype);
    data.append('zaak', zaak);
    data.append('file', file);

    for (const [property, value] of Object.entries(extraDocumentFields)) {
        data.append(property, value);
    }

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

    if (response.status >= 500) {
        throw new Error("Server error.");
    }

    const responseData = await response.json();
    return {
        ok: response.ok,
        status: response.status,
        data: responseData,
    };
};


const AddDocument = ({ zaakUrl, endpoint='/api/documents/upload', inModal=false, onUploadComplete, extraDocumentFields={} }) => {
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
        dispatch({type: 'UPLOAD_STARTED'});
        const uploadResult = await uploadFile(
            csrftoken,
            state.informatieobjecttype.value,
            state.file.value,
            zaakUrl,
            extraDocumentFields
        );
        dispatch({type: 'UPLOAD_COMPLETED'});
        if (!uploadResult.ok) {
            if (uploadResult.status === 400) {
                dispatch({
                    type: 'VALIDATION_ERRORS',
                    payload: uploadResult.data,
                });
            }
        } else {
            const documentUrl = uploadResult.data.document;
            if (onUploadComplete) {
                onUploadComplete(documentUrl);
            }
        }
    };

    if (state.uploading) {
        return (<span className="loader"></span>);
    }

    return (
        <form onSubmit={ onSubmit } className={ inModal ? 'form form--modal' : 'form' }>
            <InformatieObjectTypeSelect
                zaakUrl={ zaakUrl }
                onChange={ onFieldChange }
                value={ state.informatieobjecttype.value }
                errors={ state.informatieobjecttype.errors }
            />

            <FileInput
                name="document"
                label="Document"
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
    onUploadComplete: PropTypes.func,
    extraDocumentFields: PropTypes.object,
};


const InformatieObjectTypeSelect = ({ zaakUrl, value='', errors=[], onChange }) => {
    const asyncState = useAsync(
        async () => await getInformatieObjectTypen(zaakUrl),
        [zaakUrl]
    );

    if (asyncState.loading) {
        return (<span className="loader" />);
    }

    return (
        <Select
            name="informatieobjecttype"
            label="Documenttype"
            choices={ [['', '-------'], ...asyncState.value.map( iot => [iot.url, iot.omschrijving] )] }
            id="id_informatieobjecttype"
            helpText="Kies een relevant documenttype. Je ziet de documenttypes die bij het zaaktype horen."
            onChange={ onChange }
            value={ value }
            errors={ errors }
            required
        />
    );


};

InformatieObjectTypeSelect.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    value: PropTypes.string,
    errors: PropTypes.arrayOf(PropTypes.string),
    onChange: PropTypes.func.isRequired,
};

const getInformatieObjectTypen = async (zaakUrl) => {
    const url = `${ENDPOINT_GET_ZIO}?zaak=${encodeURI(zaakUrl)}`;
    const ioTypen = await get(url);
    return ioTypen;
};


export { AddDocument };
