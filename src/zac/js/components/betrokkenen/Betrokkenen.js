import React, { useState } from 'react';
import PropTypes from 'prop-types';
import classnames from 'classnames';
import BetrokkenenModal from './BetrokkenenModal';

const BetrokkenenRow = ({
    systemType,
    type,
    role,
    name,
    identification,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const openModal = () => setIsOpen(true);

    // Row is only clickable if there is a bsn available
    const clickable = systemType === 'natuurlijk_persoon' && identification;

    return (
        <>
            <tr
                onClick={clickable ? openModal : null}
                className={classnames(
                    'table__column',
                    { 'table__column--clickable': clickable },
                )}
                title="Toon formulier"
            >
                <td>{type}</td>
                <td>{role}</td>
                <td>{name}</td>
                <td>{identification}</td>
            </tr>
            <BetrokkenenModal
                isOpen={isOpen}
                setIsOpen={setIsOpen}
                bsn={identification}
            />
        </>
    );
};

BetrokkenenRow.propTypes = {
    systemType: PropTypes.string,
    type: PropTypes.string,
    role: PropTypes.string,
    name: PropTypes.string,
    identification: PropTypes.string,
};

const BetrokkenenTable = ({ betrokkeneNodes }) => {
    const rows = [...betrokkeneNodes].map((node) => {
        const {
            systemType, type, role, name, identification,
        } = node.dataset;
        return (
            <BetrokkenenRow
                systemType={systemType}
                type={type}
                role={role}
                name={name}
                identification={identification}
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
