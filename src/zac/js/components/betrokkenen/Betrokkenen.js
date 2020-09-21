import React, { useState } from 'react';
import PropTypes from 'prop-types';
import classnames from 'classnames';
import BetrokkenenModal from './BetrokkenenModal';

const BetrokkenenRow = ({
    type,
    role,
    name,
    bsn,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const openModal = () => setIsOpen(true);

    return (
        <>
            <tr
                // Row is only clickable if there is a bsn available
                onClick={bsn ? openModal : null}
                className={classnames(
                    'table__column',
                    { 'table__column--clickable': bsn },
                )}
                title="Toon formulier"
            >
                <td>{type}</td>
                <td>{role}</td>
                <td>{name}</td>
                <td>{bsn}</td>
            </tr>
            <BetrokkenenModal
                isOpen={isOpen}
                setIsOpen={setIsOpen}
                bsn={bsn}
            />
        </>
    );
};

BetrokkenenRow.propTypes = {
    type: PropTypes.string,
    role: PropTypes.string,
    name: PropTypes.string,
    bsn: PropTypes.string,
};

const BetrokkenenTable = ({ betrokkeneNodes }) => {
    const rows = [...betrokkeneNodes].map((node) => {
        const {
            type, role, name, bsn,
        } = node.dataset;
        return (
            <BetrokkenenRow
                type={type}
                role={role}
                name={name}
                bsn={bsn}
                key={name}
            />
        );
    });

    return (
        <table className="table table--fit">
            <thead>
                <tr>
                    <th className="table__header table__column table__column--4cols">Type</th>
                    <th className="table__header table__column table__column--2cols">Rol</th>
                    <th className="table__header table__column table__column--4cols">Naam</th>
                    <th className="table__header table__column table__column--2cols">Identificatie</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    );
};

BetrokkenenTable.propTypes = {
    betrokkeneNodes: PropTypes.any, // NodeList
};

export default BetrokkenenTable;
