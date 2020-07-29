import React from "react";
import moment from "moment";
import 'moment/locale/nl.js';

import {getAuthorName} from "./utils";

moment.locale('nl');


const AdviceRow = ({ advice }) =>
    <tr>
        <td>{advice.advice}</td>
        <td>{getAuthorName(advice.author)}</td>
        <td>{moment(advice.created).fromNow()}</td>
        <td>{advice.documents.length}</td>
    </tr>
;


const AdviceTable = ({ advices }) => {
    const rows = advices.map((advice, index) =>
        <AdviceRow key={index} advice={advice}/>
    );

    return (
        <section className="zaak-detail__panel zaak-detail__panel--full content-panel">
            <div className="section-title">Adviezen</div>
            {!(advices.length) ?
                <p className="content-panel__content content-panel__content--blurred">
                    (geen adviezen)
                </p>
                : <table className="table">
                    <thead>
                    <tr>
                        <th className="table__header">Advies</th>
                        <th className="table__header">Van</th>
                        <th className="table__header">Gegeven op</th>
                        <th className="table__header">Documentadviezen</th>
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


export { AdviceTable };
