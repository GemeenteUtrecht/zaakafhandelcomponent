import React, { useContext, useRef, useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import { useAsync } from 'react-use';
import { useImmerReducer } from "use-immer";

import { apiCall, get } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { Select } from '../forms/Select';
import { SubmitRow } from '../forms/Utils';
import { IconedText } from '../IconedText';
import { Activity } from './types';


const ENDPOINT_GET_ZIO = '/core/api/documents/get-informatieobjecttypen';


const getInformatieObjectTypen = async (zaakUrl) => {
    const url = `${ENDPOINT_GET_ZIO}?zaak=${encodeURI(zaakUrl)}`;
    const ioTypen = await get(url);
    return ioTypen;
};


const initialState = {
    informatieobjecttype: {
        value: '',
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


const AddDocument = ({ zaakUrl, endpoint='/api/documents/upload' }) => {
    const csrftoken = useContext(CsrfTokenContext);
    const fileInput = useRef(null);
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

        // prepare multipart file upload
        const data = new FormData();
        data.append('csrfmiddlewaretoken', csrftoken);
        data.append('file', fileInput.current.files[0]);

        // send the API call
        const response = await apiCall(
            ENDPOINT,
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

    const { loading, value } = useAsync(
        async () => await getInformatieObjectTypen(zaakUrl),
        [zaakUrl]
    );

    if (loading) {
        return (<span className="loader" />);
    }

    return (
        <form onSubmit={ onSubmit } className="form form--modal">

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

            <label>
                Document:
                <input type="file" ref={ fileInput } name="document" />
            </label>

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


const CaseActivityDocument = ({ activity, canMutate=false }) => {
    // TODO: flesh out more
    if (activity.document) {
        return (
            <a className="btn btn--small" onClick={() => alert('todo')}>
                Toon documentinformatie
            </a>
        );
    }

    if (!canMutate) {
        return (
            <span className="soft-info soft-info--normal-size">
                Document ontbreekt.
            </span>
        );
    }

    const [isAdding, setIsAdding] = useState(false);

    const closeModal = () => setIsAdding(false);

    return (
        <React.Fragment>
            {'Document: '}
            <button
                type="button"
                className="btn btn--small"
                onClick={ () => setIsAdding(true) }
            >
                <IconedText icon="attach_file">Toevoegen</IconedText>
            </button>

            <Modal
              isOpen={ isAdding }
              className="modal"
              onRequestClose={ closeModal }
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <h1 className="page-title">Document toevoegen</h1>
                <AddDocument zaakUrl={activity.zaak} />
            </Modal>

        </React.Fragment>
    );
};

CaseActivityDocument.propTypes = {
    activity: Activity.isRequired,
    canMutate: PropTypes.bool,
};


export { CaseActivityDocument };
