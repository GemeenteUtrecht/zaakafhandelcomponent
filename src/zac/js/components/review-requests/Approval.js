import React from "react";
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { getUserName } from '../../utils/users';

/**
 * A table row, containing information about single approval
 * @param   {Object}    approval   An object with a single approval data
 * @return  {JSX}
 */
const ApprovalRow = ({approval}) =>
    <tr>
        <td>{approval.approved ? 'Approved' : 'Not approved'}</td>
        <td>{getUserName(approval.author)}</td>
        <td>{timeSince(approval.created)}</td>
    </tr>
;

ApprovalRow.propTypes = {
    approval: PropTypes.object.isRequired,
};


/**
 * A table displaying approvals of a single review request
 * @param   {Array}  approvals A list of the approval objects
 * @return  {JSX}
 */
const ApprovalTable = ({ approvals }) => {
    const rows = approvals.map((approval, index) =>
        <ApprovalRow key={index} approval={approval}/>
    );

    return (
        <section className="zaak-detail__panel zaak-detail__panel--full content-panel">
            <div className="section-title">Approvals</div>
            {!(approvals.length) ?
                <p className="content-panel__content content-panel__content--blurred">
                    (geen accordering)
                </p>
                : <table className="table">
                    <thead>
                    <tr>
                        <th className="table__header">Approval</th>
                        <th className="table__header">Van</th>
                        <th className="table__header">Gegeven op</th>
                    </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            }
        </section>
    );
};

ApprovalTable.propTypes = {
    approvals: PropTypes.arrayOf(PropTypes.object.isRequired).isRequired,
};


export { ApprovalTable };
