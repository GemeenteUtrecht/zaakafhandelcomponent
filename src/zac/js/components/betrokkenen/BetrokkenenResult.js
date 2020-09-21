import React, { useEffect } from 'react';
import PropTypes from 'prop-types';

const StringResult = ({ title, value }) => (
    <div className="result">
        <h3 className="result__title">{title}</h3>
        <p className="result__value">{value}</p>
    </div>
);

StringResult.propTypes = {
    title: PropTypes.string,
    value: PropTypes.string,
};

const ArrayResult = ({ title, data }) => (
    <div className="result">
        <h3 className="result__title">{title}</h3>
        <div className="subresult">
            {data.map((item, index) => {
                const key = index;
                return (
                    <div className="subresult__row" key={key}>
                        <div className="subresult__group">
                            {/* Naam */}
                            <p className="subresult__title">Naam</p>
                            <p className="subresult__value">{item.naam}</p>
                        </div>

                        <div className="subresult__group">
                            {/* Geboortedatum */}
                            <p className="subresult__title">Geboortedatum</p>
                            <p className="subresult__value">{item.geboortedatum}</p>
                        </div>

                        <div className="subresult__group">
                            {/* Burgerservicenummer */}
                            <p className="subresult__title">BSN</p>
                            <p className="subresult__value">{item.burgerservicenummer}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    </div>
);

ArrayResult.propTypes = {
    title: PropTypes.string,
    data: PropTypes.arrayOf(PropTypes.object),
};

const AddressResult = ({ title, data }) => {
    const { adres, postcode, woonplaats } = data;
    return (
        <div className="result">
            <h3 className="result__title">{title}</h3>
            <div className="subresult">
                <div className="subresult__row">
                    {/* Adres */}
                    <p className="subresult__title">Adres</p>
                    <div className="subresult__group">
                        <p className="subresult__value">{adres}</p>
                        <br />
                        <p className="subresult__value">{`${postcode}, ${woonplaats}`}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

AddressResult.propTypes = {
    title: PropTypes.string,
    data: PropTypes.objectOf(PropTypes.string),
};

const BetrokkenenResult = ({ data, closeModal }) => {
    // When escape is pressed
    const escFunction = (event) => {
        if (event.keyCode === 27) {
            closeModal();
        }
    };

    useEffect(() => {
        document.addEventListener('keydown', escFunction, false);
        return () => {
            document.removeEventListener('keydown', escFunction, false);
        };
    }, []);

    return (
        <div className="form form--modal">
            <h2 className="section-title">Resultaten bijkomende gegevens:</h2>

            {/* Geboortedatum */}
            {data.geboortedatum && <StringResult title="Geboortedatum" value={data.geboortedatum} />}

            {/* Geboorteland */}
            {data.geboorteland && <StringResult title="Geboorteland" value={data.geboorteland} />}

            {/* NAW */}
            {data.verblijfplaats && <AddressResult title="NAW" data={data.verblijfplaats} />}

            {/* Kinderen */}
            {data.kinderen && <ArrayResult title="Kinderen" data={data.kinderen} />}

            {/* Partners */}
            {data.partners && <ArrayResult title="Partners" data={data.partners} />}
        </div>
    );
};

BetrokkenenResult.propTypes = {
    data: PropTypes.shape({
        geboortedatum: PropTypes.string,
        geboorteland: PropTypes.string,
        kinderen: PropTypes.arrayOf(PropTypes.object),
        partners: PropTypes.arrayOf(PropTypes.object),
        verblijfplaats: PropTypes.objectOf(PropTypes.string),
    }),
    closeModal: PropTypes.func,
};

export default BetrokkenenResult;
