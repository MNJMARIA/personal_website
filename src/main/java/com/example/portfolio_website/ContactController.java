package com.example.portfolio_website;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/contact")
@CrossOrigin(origins = {
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://mariiastepanova.netlify.app"
})
public class ContactController {
    private final MailService mailService;

    public ContactController(MailService mailService) {
        this.mailService = mailService;
    }

    @PostMapping
    public ResponseEntity<String> send(
            @Valid @RequestBody ContactRequest request
    ) {

        mailService.save(request);

        return ResponseEntity.ok("Message saved");
    }
}
