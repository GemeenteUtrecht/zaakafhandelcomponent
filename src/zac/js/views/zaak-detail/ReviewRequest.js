import React, { useState } from "react";
import Modal from 'react-modal';

import {AdviceTable} from "./Advice";
import {ApprovalTable} from "./Approval";


const kownslTypes = {
    advice: 'Advies',
    approval: 'Accordering'
};


const ReviewRequestModal = ({ isOpen, setIsOpen, reviewRequest }) => {
    const closeModal = () => setIsOpen(false);
    console.log("reviewRequest=", reviewRequest);

    return (
        <Modal isOpen={isOpen}>
            <button onClick={closeModal} className="modal__close btn">&times;</button>

            <AdviceTable advices={reviewRequest.advices}/>
            <ApprovalTable approvals={reviewRequest.approvals}/>
        </Modal>
    );
};


const ReviewRequestRow = ({ reviewRequest }) => {
    const numReviews = reviewRequest.review_type === 'advice' ? reviewRequest.num_advices : reviewRequest.num_approvals;
    // modal
    const [isOpen, setIsOpen] = useState(false);
    const openModal = () => setIsOpen(true);

    return (
        <>
            <tr onClick={openModal}>
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

export { ReviewRequestTable };
