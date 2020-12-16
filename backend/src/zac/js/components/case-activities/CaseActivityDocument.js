import React, { useContext, useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import { useAsync } from 'react-use';

import { get, patch } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { IconedText } from '../IconedText';
import { AddDocument } from '../documents/AddDocument';
import { ActivitiesContext } from './context';
import { Activity } from './types';


const ENDPOINT_DOCUMENT_INFO = '/core/api/documents/info';


const getDocumentInfo = async (documentUrl) => {
    const url = `${ENDPOINT_DOCUMENT_INFO}?document=${encodeURI(documentUrl)}`;
    return (await get(url));
};


const DocumentPreview = ({ documentUrl }) => {
    const { loading, value } = useAsync(
        async () => await getDocumentInfo(documentUrl),
        [documentUrl]
    );

    if (loading) {
        return (<span className="loader" />);
    }

    return (
        <div className="document-preview">
            <i className="document-preview__icon material-icons">
                insert_drive_file
            </i>

            <span className="document-preview__meta">
                <a href={value.downloadUrl}
                   className="link"
                   target="_blank"
                   rel="noopener nofollower">{ value.titel }</a> &nbsp;
                { value.bestandsgrootte }
                <br/>
                { value.documentType } ({ value.vertrouwelijkheidaanduiding })
            </span>
        </div>
    );
};

DocumentPreview.propTypes = {
    documentUrl: PropTypes.string.isRequired,
};


const CaseActivityDocument = ({ activity, canMutate=false }) => {
    const activitiesContext = useContext(ActivitiesContext);
    const csrftoken = useContext(CsrfTokenContext);

    if (activity.document) {
        return (<DocumentPreview documentUrl={ activity.document } />);
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
            <a
                href="#"
                role="button"
                className="link link--inline-action"
                onClick={ (e) => {
                    e.preventDefault();
                    setIsAdding(true);
                } }
            > Document toevoegen </a>

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
                    inModal
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
