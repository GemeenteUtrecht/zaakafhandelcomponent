import React, { useState } from "react";

const kownslTypes = {
    advice: 'Advies',
    approval: 'Accordering'
};


const ReviewRequestRow = ({ reviewRequest }) => {
    const numReviews = reviewRequest.review_type === 'advice' ? reviewRequest.num_advices : reviewRequest.num_approvals;
    return (
        <tr>
            <td>{kownslTypes[reviewRequest.review_type]}</td>
            <td>{`${numReviews} / ${reviewRequest.num_assigned_users}`}</td>
        </tr>
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
