import React from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { getUserName } from '../../utils/users';
import { IconedText } from '../IconedText';

/**
 * A table row, containing information about single approval
 * @param   {Object}    approval   An object with a single approval data
 * @return  {JSX}
 */
const ApprovalRow = ({ approval }) => (
    <tr>
        <td>
            {
                approval.approved
                    ? <IconedText icon="done">Akkoord</IconedText>
                    : <IconedText icon="block">Niet akkoord</IconedText>
            }
        </td>
        <td>{getUserName(approval.author)}</td>
        <td>{timeSince(approval.created)}</td>
        <td>{approval.toelichting}</td>

    </tr>
);

ApprovalRow.propTypes = {
    approval: PropTypes.object.isRequired,
};

/**
 * A table displaying approvals of a single review request
 * @param   {Array}  approvals A list of the approval objects
 * @return  {JSX}
 */
const ApprovalTable = ({ approvals }) => {
    if (!approvals.length) {
        return (
            <p className="soft-info soft-info--normal-size">
                Er zijn (nog) geen accorderingen opgevoerd.
            </p>
        );
    }

    const rows = approvals.map((approval, index) => <ApprovalRow key={index} approval={approval} />);

    return (
        <table className="table table--comfortable">
            <thead>
                <tr>
                    <th className="table__header">Akkoord?</th>
                    <th className="table__header">Van</th>
                    <th className="table__header">Gegeven op</th>
                    <th className="table__header">Toelichting</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    );
};

ApprovalTable.propTypes = {
    approvals: PropTypes.arrayOf(PropTypes.object.isRequired).isRequired,
};

export { ApprovalTable };
