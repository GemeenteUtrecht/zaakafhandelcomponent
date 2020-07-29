import React from "react";
import {getAuthorName} from "./utils";


const ApprovalRow = ({approval}) =>
    <tr>
        <td>{approval.approved ? 'Approved' : 'Not approved'}</td>
        <td>{getAuthorName(approval.author)}</td>
        <td>{approval.created}</td>
    </tr>
;


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


export { ApprovalTable };
