import React from "react";
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { getUserName } from '../../utils/users';


const ApprovalText = ({ icon, children }) => {
    return (
        <span className="iconed-text">
            <i className="material-icons iconed-text__icon">{icon}</i>
            {children}
        </span>
    );
};


/**
 * A table row, containing information about single approval
 * @param   {Object}    approval   An object with a single approval data
 * @return  {JSX}
 */
const ApprovalRow = ({approval}) =>
    <tr>
        <td>
            {
                approval.approved
                ? <ApprovalText icon="done">Akkoord</ApprovalText>
                : <ApprovalText icon="block">Niet akkoord</ApprovalText>
            }
        </td>
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
    if (!approvals.length) {
        return (
            <p className="soft-info soft-info--normal-size">
                Er zijn (nog) geen accorderingen opgevoerd.
            </p>
        );
    }

    const rows = approvals.map((approval, index) =>
        <ApprovalRow key={index} approval={approval}/>
    );

    return (
        <table className="table table--comfortable">
            <thead>
                <tr>
                    <th className="table__header">Akkoord?</th>
                    <th className="table__header">Van</th>
                    <th className="table__header">Gegeven op</th>
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
