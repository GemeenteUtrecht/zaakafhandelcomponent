import React, { useState } from "react";
import Modal from 'react-modal';
import PropTypes from 'prop-types';

import {AdviceTable} from "./Advice";
import {ApprovalTable} from "./Approval";


const kownslTypes = {
    advice: 'Advies',
    approval: 'Accordering'
};


const modalStyles = {
  overlay : {zIndex: '100'}
};


/**
 * A modal window, containing information about advices or approvals of the selected review request
 * @return  {JSX}
 */
const ReviewRequestModal = ({ isOpen, setIsOpen, reviewRequest }) => {
    const closeModal = () => setIsOpen(false);

    return (
        <Modal isOpen={isOpen} className="modal" style={modalStyles}>
            <button onClick={closeModal} className="modal__close btn">&times;</button>
            <h1 className="page-title">{`Review request for ${reviewRequest.review_type}`}</h1>

            {reviewRequest.review_type === 'advice'
                ? <AdviceTable advices={reviewRequest.advices}/>
                : <ApprovalTable approvals={reviewRequest.approvals}/>
            }
        </Modal>
    );
};

ReviewRequestModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    setIsOpen: PropTypes.func.isRequired,
    reviewRequest: PropTypes.object.isRequired,
};


/**
 * A table row, containing information about single review request and allowing the display of modal on click
 * @param   {Object}    reviewRequest   An object with a single review request data
 * @return  {JSX}
 */
const ReviewRequestRow = ({ reviewRequest }) => {
    const numReviews = reviewRequest.review_type === 'advice' ? reviewRequest.num_advices : reviewRequest.num_approvals;
    // modal
    const [isOpen, setIsOpen] = useState(false);
    const openModal = () => setIsOpen(true);

    return (
        <>
            <tr onClick={openModal} className="table__column table__column--clickable">
                <td>{kownslTypes[reviewRequest.review_type]}</td>
                <td>{`${numReviews} / ${reviewRequest.num_assigned_users}`}</td>
            </tr>
            <ReviewRequestModal
                isOpen={isOpen}
                setIsOpen={setIsOpen}
                reviewRequest={reviewRequest}
            />
        </>
    );
};

ReviewRequestRow.propTypes = {
    reviewRequest: PropTypes.object.isRequired,
};


/**
 * A review request table allowing the display of related advices and approvals in the modal
 * @param   {Array}  reviewRequests A list of the review requests objects
 * @return  {JSX}
 */
const ReviewRequestTable = ({ reviewRequests }) => {
    const rows = reviewRequests.map( (reviewRequest) =>
        <ReviewRequestRow reviewRequest={reviewRequest} key={reviewRequest.id}/>
    );

    return (
        <table className="table">
            <thead>
            <tr>
                <th className="table__header">Type</th>
                <th className="table__header"># Opgehaald</th>
            </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    );
};

ReviewRequestTable.propTypes = {
    reviewRequests: PropTypes.arrayOf(PropTypes.object).isRequired,
};


export { ReviewRequestTable };
