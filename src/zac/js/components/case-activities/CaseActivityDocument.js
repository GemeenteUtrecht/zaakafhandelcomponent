import React, { useContext, useRef, useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import { useAsync } from 'react-use';

import { apiCall } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { SubmitRow } from '../forms/Utils';
import { IconedText } from '../IconedText';
import { Activity } from './types';


const ENDPOINT = '/api/documents/upload';


const AddDocument = ({ zaakUrl }) => {
    const csrftoken = useContext(CsrfTokenContext);
    const fileInput = useRef(null);

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

    return (
        <form onSubmit={ onSubmit }>

            {/* IOT choice */}

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
