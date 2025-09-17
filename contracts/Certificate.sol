// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificateVerification {
    struct Certificate {
        string studentName;
        string course;
        string institution;
        uint256 issueDate;
        string certHash; // IPFS CID or SHA256 string
        bool isValid;
    }

    mapping(string => Certificate) private certificates; // certID => Certificate
    address public owner;

    event CertificateIssued(string certID, address issuer);
    event CertificateRevoked(string certID, address issuer);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner allowed");
        _;
    }

    function issueCertificate(
        string calldata certID,
        string calldata studentName,
        string calldata course,
        string calldata institution,
        string calldata certHash
    ) external onlyOwner {
        certificates[certID] = Certificate(
            studentName,
            course,
            institution,
            block.timestamp,
            certHash,
            true
        );
        emit CertificateIssued(certID, msg.sender);
    }

    function revokeCertificate(string calldata certID) external onlyOwner {
        certificates[certID].isValid = false;
        emit CertificateRevoked(certID, msg.sender);
    }

    function verifyCertificate(string calldata certID, string calldata certHash)
        external
        view
        returns (
            bool valid,
            string memory studentName,
            string memory course,
            string memory institution,
            uint256 issueDate
        )
    {
        Certificate memory c = certificates[certID];
        bool hashMatches = (keccak256(bytes(c.certHash)) == keccak256(bytes(certHash)));
        return (c.isValid && hashMatches, c.studentName, c.course, c.institution, c.issueDate);
    }
}
