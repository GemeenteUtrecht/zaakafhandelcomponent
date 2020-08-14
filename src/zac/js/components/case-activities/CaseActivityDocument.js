import React, { useContext, useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';

import { patch } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { IconedText } from '../IconedText';
import { AddDocument } from '../documents/AddDocument';
import { ActivitiesContext } from './context';
import { Activity } from './types';


const CaseActivityDocument = ({ activity, canMutate=false }) => {
    const activitiesContext = useContext(ActivitiesContext);
    const csrftoken = useContext(CsrfTokenContext);

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

    const onUploadComplete = async (documentUrl) => {
        const resp = await patch(activity.url, csrftoken, {document: documentUrl});
        if (!resp.ok) {
            console.error(resp.data);
        }
        activitiesContext.refresh();
    };

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
                <AddDocument
                    zaakUrl={activity.zaak}
                    onUploadComplete={ onUploadComplete }
                    extraDocumentFields={{
                        beschrijving: `Document voor activiteit '${activity.name}'`,
                    }}
                />
            </Modal>

        </React.Fragment>
    );
};

CaseActivityDocument.propTypes = {
    activity: Activity.isRequired,
    canMutate: PropTypes.bool,
};


export { CaseActivityDocument };
